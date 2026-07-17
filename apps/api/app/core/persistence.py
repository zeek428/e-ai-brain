from __future__ import annotations

from pathlib import Path
from time import sleep
from typing import Any

from app.core.db import DatabaseConnectionPool
from app.core.persistence_repositories import install_snapshot_repositories
from app.core.persistence_runtime import PostgresRuntimeStore as PostgresRuntimeStore
from app.core.persistent_memory_store import PersistentMemoryStore as PersistentMemoryStore
from app.core.product_version_dashboard_read_model import product_version_dashboard_source_rows
from app.core.repositories.rd_collaboration import RdCollaborationReadRepository


class PostgresSnapshotRepository(RdCollaborationReadRepository):
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
        # Collaboration is a concrete mixin boundary so static and runtime structural
        # contracts see the same methods. Keep the compatibility attribute for callers
        # that historically inspected the registered repository.
        self._rd_collaboration_read_repository = self
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
                self._apply_additive_migration(
                    cursor,
                    "053_menu_management.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "054_assistant_action_drafts.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "055_code_inspection_native_scan.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "056_code_inspection_scan_snapshot.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "057_assistant_analysis_drafts.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "058_assistant_action_draft_expiry.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "059_assistant_rd_task_drafts.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "060_scheduled_job_run_permission.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "061_assistant_metrics_and_role_quick_tasks.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "062_assistant_action_draft_idempotency.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "063_assistant_chat_runs.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "064_assistant_action_reference_configs.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "065_assistant_operability_improvements.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "066_rd_task_executor_policies.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "067_execution_trace_diagnostics.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "068_assistant_draft_workbench.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "069_execution_trace_read_model.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "070_code_inspection_suppression_approval.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "071_ai_executor_task_dead_letter.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "072_code_inspection_incremental_snapshot.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "073_code_inspection_risk_acceptance_expiry.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "074_internal_data_source_plugin.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "075_internal_data_source_detail_permission.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "076_assistant_action_naming.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "077_ai_agent_packages.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "078_ai_executor_approval_requests.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "079_plugin_invocation_log_nullable_config_refs.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "080_system_settings.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "081_dingtalk_mcp_plugins.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "082_dingtalk_login_external_identities.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "083_viewer_menu_task_boundary.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "084_viewer_assistant_menu_boundary.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "085_viewer_product_read_menu.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "086_dingtalk_oauth_ephemeral_states.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "087_user_profile_contact.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "088_dingtalk_corp_name.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "089_user_password_login_state.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "090_role_boundary_cleanup.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "091_knowledge_hybrid_search_indexes.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "092_auth_login_challenges.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "093_bug_fix_task_type.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "094_rd_task_executor_policy_code_change_review_mode.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "095_system_health_center.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "096_platform_operations_quality_loop.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "097_system_alert_rules_and_admin_report.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "098_system_alert_notifications.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "099_deployment_requests.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "100_operational_deployment_menu.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "101_deployment_strategies.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "102_autonomous_delivery_governance.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "103_deployment_safety_enforcement.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "104_execution_resource_menu.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "105_knowledge_multimodal_governance.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "106_trusted_execution_attestations.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "107_trusted_delivery_records.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "109_requirement_driven_rd_collaboration.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "110_unified_rd_execution_policy.sql",
                )
                self._apply_additive_migration(
                    cursor,
                    "111_requirement_assessment_orchestration.sql",
                )

    def next_id(self, prefix: str) -> str:
        return self._system_state_repository.next_id(prefix)

    def _apply_additive_migration(self, cursor: Any, filename: str) -> None:
        migration_path = Path(__file__).resolve().parents[1] / "db" / "migrations" / filename
        if not migration_path.exists():
            return
        sql = migration_path.read_text(encoding="utf-8").strip()
        if sql:
            cursor.execute(sql)

    def load(self) -> dict[str, Any] | None:
        return self._system_state_repository.load_snapshot()

    def save(self, payload: dict[str, Any]) -> None:
        self._system_state_repository.save_snapshot(payload)

    def get_system_settings(self) -> dict[str, Any]:
        return self._system_settings_repository.get_system_settings()

    def upsert_system_settings(
        self,
        settings: dict[str, Any],
        *,
        actor_id: str | None = None,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._system_settings_repository.upsert_system_settings(
            settings,
            actor_id=actor_id,
            audit_event=audit_event,
        )

    def list_system_alert_incidents(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return self._platform_operations_repository.list_system_alert_incidents(limit=limit)

    def upsert_system_alert_incidents(
        self,
        alerts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._platform_operations_repository.upsert_system_alert_incidents(alerts)

    def update_system_alert_incident(
        self,
        alert_id: str,
        *,
        close_reason: str | None = None,
        history_event: dict[str, Any] | None = None,
        owner: str | None = None,
        postmortem: str | None = None,
        status: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any] | None:
        return self._platform_operations_repository.update_system_alert_incident(
            alert_id,
            close_reason=close_reason,
            history_event=history_event,
            owner=owner,
            postmortem=postmortem,
            status=status,
            actor_id=actor_id,
        )

    def list_system_alert_notifications(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._platform_operations_repository.list_system_alert_notifications(
            limit=limit,
            status=status,
        )

    def upsert_system_alert_notifications(
        self,
        notifications: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._platform_operations_repository.upsert_system_alert_notifications(notifications)

    def update_system_alert_notification_status(
        self,
        notification_id: str,
        *,
        delivery_result: dict[str, Any] | None = None,
        last_error: str | None = None,
        status: str,
    ) -> dict[str, Any] | None:
        return self._platform_operations_repository.update_system_alert_notification_status(
            notification_id,
            delivery_result=delivery_result,
            last_error=last_error,
            status=status,
        )

    def list_system_alert_subscriptions(self) -> list[dict[str, Any]]:
        return self._platform_operations_repository.list_system_alert_subscriptions()

    def save_system_alert_subscription(self, subscription: dict[str, Any]) -> dict[str, Any]:
        return self._platform_operations_repository.save_system_alert_subscription(subscription)

    def list_system_alert_rules(self) -> list[dict[str, Any]]:
        return self._platform_operations_repository.list_system_alert_rules()

    def save_system_alert_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        return self._platform_operations_repository.save_system_alert_rule(rule)

    def insert_knowledge_quality_event(self, event: dict[str, Any]) -> dict[str, Any]:
        return self._platform_operations_repository.insert_knowledge_quality_event(event)

    def list_knowledge_quality_events(
        self,
        *,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self._platform_operations_repository.list_knowledge_quality_events(
            event_type=event_type,
            limit=limit,
        )

    def knowledge_quality_summary(self, *, since_days: int = 30) -> dict[str, Any]:
        return self._platform_operations_repository.knowledge_quality_summary(
            since_days=since_days,
        )

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
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
    ) -> int:
        return self._product_config_read_repository.count_product_summaries(
            active_only=active_only,
            code=code,
            name=name,
            owner_team=owner_team,
            product_scope_ids=product_scope_ids,
            status=status,
        )

    def list_product_summaries(
        self,
        *,
        active_only: bool = False,
        code: str | None = None,
        name: str | None = None,
        owner_team: str | None = None,
        product_scope_ids: list[str] | None = None,
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
            product_scope_ids=product_scope_ids,
            status=status,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    def get_product(self, product_id: str) -> dict[str, Any] | None:
        return self._product_config_read_repository.get_product(product_id)

    def get_product_version(self, version_id: str) -> dict[str, Any] | None:
        return self._product_config_read_repository.get_product_version(version_id)

    def get_product_git_repository(self, repository_id: str) -> dict[str, Any] | None:
        return self._product_config_read_repository.get_product_git_repository(repository_id)

    def get_product_module(self, module_id: str) -> dict[str, Any] | None:
        return self._product_config_read_repository.get_product_module(module_id)

    def product_module_has_related_records(self, product_id: str, module_code: str) -> bool:
        return self._product_config_read_repository.product_module_has_related_records(
            product_id,
            module_code,
        )

    def product_has_related_records(self, product_id: str) -> bool:
        return self._product_config_read_repository.product_has_related_records(product_id)

    def product_version_has_related_records(self, version_id: str) -> bool:
        return self._product_config_read_repository.product_version_has_related_records(
            version_id,
        )

    def get_related_system(self, system_id: str) -> dict[str, Any] | None:
        return self._product_config_read_repository.get_related_system(system_id)

    def get_related_system_by_code(self, code: str) -> dict[str, Any] | None:
        return self._product_config_read_repository.get_related_system_by_code(code)

    def get_product_version_branch_config(
        self,
        branch_config_id: str,
    ) -> dict[str, Any] | None:
        return self._product_config_read_repository.get_product_version_branch_config(
            branch_config_id,
        )

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
        product_scope_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        list_kwargs: dict[str, Any] = {
            "active_only": active_only,
            "product_id": product_id,
        }
        if product_scope_ids is not None:
            list_kwargs["product_scope_ids"] = product_scope_ids
        return self._product_config_read_repository.list_related_systems(**list_kwargs)

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
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
    ) -> int:
        return self._product_config_read_repository.count_product_version_summaries(
            active_only=active_only,
            code=code,
            name=name,
            product=product,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
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
        product_scope_ids: list[str] | None = None,
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
            product_scope_ids=product_scope_ids,
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
        product_scope_ids: list[str] | None = None,
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
            product_scope_ids=product_scope_ids,
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
        product_scope_ids: list[str] | None = None,
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
            product_scope_ids=product_scope_ids,
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
        product_scope_ids: list[str] | None = None,
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
            product_scope_ids=product_scope_ids,
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
        product_scope_ids: list[str] | None = None,
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
            product_scope_ids=product_scope_ids,
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
        product_scope_ids: list[str] | None = None,
        read_scope: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._task_read_repository.list_pending_review_summaries(
            product_scope_ids=product_scope_ids,
            read_scope=read_scope,
        )

    def load_ai_tasks(self) -> dict[str, Any]:
        return self._task_read_repository.load_ai_tasks()

    def load_workflow_runtime(self) -> dict[str, Any]:
        return self._task_read_repository.load_workflow_runtime()

    def get_task_workflow_source_rows(self) -> dict[str, Any]:
        audit_payload = self.load_audit_events() or {}
        bugs_payload = self.load_bugs() or {}
        deployments_payload = self.load_deployment_requests() or {}
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
            "code_inspection_reports": self.list_code_inspection_reports(),
            "code_review_reports": list((review_payload.get("code_review_reports") or {}).values()),
            "deployment_requests": list(
                (deployments_payload.get("deployment_requests") or {}).values()
            ),
            "deployment_schemes": list(
                (deployments_payload.get("deployment_schemes") or {}).values()
            ),
            "deployment_runs": list((deployments_payload.get("deployment_runs") or {}).values()),
            "gitlab_daily_code_metrics": list(
                (gitlab_metrics_payload.get("gitlab_daily_code_metrics") or {}).values()
            ),
            "gitlab_mr_snapshots": list((review_payload.get("gitlab_mr_snapshots") or {}).values()),
            "graph_checkpoints": list((workflow_payload.get("graph_checkpoints") or {}).values()),
            "graph_runs": list((workflow_payload.get("graph_runs") or {}).values()),
            "human_reviews": list((workflow_payload.get("human_reviews") or {}).values()),
            "jenkins_release_records": list(
                (jenkins_releases_payload.get("jenkins_release_records") or {}).values()
            ),
            "knowledge_chunks": list((knowledge_payload.get("knowledge_chunks") or {}).values()),
            "knowledge_deposits": list(
                (knowledge_payload.get("knowledge_deposits") or {}).values()
            ),
            "knowledge_documents": list(
                (knowledge_payload.get("knowledge_documents") or {}).values()
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
            "product_modules": list((product_config_payload.get("product_modules") or {}).values()),
            "product_version_branch_configs": list(
                (product_config_payload.get("product_version_branch_configs") or {}).values()
            ),
            "product_versions": list(
                (product_config_payload.get("product_versions") or {}).values()
            ),
            "products": list((product_config_payload.get("products") or {}).values()),
            "related_systems": list((product_config_payload.get("related_systems") or {}).values()),
            "requirements": list((requirements_payload.get("requirements") or {}).values()),
            "tasks": list((tasks_payload.get("ai_tasks") or {}).values()),
        }

    def get_product_version_dashboard_source_rows(self, version_id: str) -> dict[str, Any]:
        return product_version_dashboard_source_rows(self, version_id)

    def load_knowledge(self) -> dict[str, Any]:
        return self._knowledge_read_repository.load_knowledge()

    def list_knowledge_spaces(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        return self._knowledge_read_repository.list_knowledge_spaces(active_only=active_only)

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

    def count_knowledge_document_summaries(
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
        permission_role: str | None = None,
    ) -> int:
        return self._knowledge_read_repository.count_knowledge_document_summaries(
            user_roles=user_roles,
            user_id=user_id,
            global_knowledge_access=global_knowledge_access,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
            keyword=keyword,
            doc_type=doc_type,
            folder_id=folder_id,
            index_status=index_status,
            knowledge_space_id=knowledge_space_id,
            permission_role=permission_role,
        )

    def list_knowledge_document_summaries_page(
        self,
        *,
        user_roles: list[str],
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        user_id: str | None = None,
        global_knowledge_access: bool = False,
        knowledge_space_scope_ids: list[str] | None = None,
        keyword: str | None = None,
        doc_type: str | None = None,
        folder_id: str | None = None,
        index_status: str | None = None,
        knowledge_space_id: str | None = None,
        permission_role: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._knowledge_read_repository.list_knowledge_document_summaries_page(
            user_roles=user_roles,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            user_id=user_id,
            global_knowledge_access=global_knowledge_access,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
            keyword=keyword,
            doc_type=doc_type,
            folder_id=folder_id,
            index_status=index_status,
            knowledge_space_id=knowledge_space_id,
            permission_role=permission_role,
        )

    def knowledge_index_health(
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
        permission_role: str | None = None,
        issue_limit: int = 10,
    ) -> dict[str, Any]:
        return self._knowledge_read_repository.knowledge_index_health(
            user_roles=user_roles,
            user_id=user_id,
            global_knowledge_access=global_knowledge_access,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
            keyword=keyword,
            doc_type=doc_type,
            folder_id=folder_id,
            index_status=index_status,
            knowledge_space_id=knowledge_space_id,
            permission_role=permission_role,
            issue_limit=issue_limit,
        )

    def list_knowledge_deposits(
        self,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._knowledge_read_repository.list_knowledge_deposits(status=status)

    def count_knowledge_deposits(
        self,
        *,
        status: str | None = None,
    ) -> int:
        return self._knowledge_read_repository.count_knowledge_deposits(status=status)

    def list_knowledge_deposits_page(
        self,
        *,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._knowledge_read_repository.list_knowledge_deposits_page(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
        )

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
        product_id: str | None = None,
        query: str | None = None,
        version_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._knowledge_read_repository.search_knowledge_chunks(
            user_roles=user_roles,
            user_id=user_id,
            global_knowledge_access=global_knowledge_access,
            knowledge_space_id=knowledge_space_id,
            knowledge_space_scope_ids=knowledge_space_scope_ids,
            product_id=product_id,
            query=query,
            version_id=version_id,
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
        product_scope_ids: list[str] | None = None,
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
            product_scope_ids=product_scope_ids,
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
        product_scope_ids: list[str] | None = None,
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
            product_scope_ids=product_scope_ids,
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

    def load_deployment_requests(self) -> dict[str, Any]:
        return self._devops_read_repository.load_deployment_requests()

    def list_deployment_schemes(
        self,
        *,
        deployment_method: str | None = None,
        environment: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheme_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._devops_read_repository.list_deployment_schemes(
            deployment_method=deployment_method,
            environment=environment,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            scheme_id=scheme_id,
            status=status,
        )

    def list_deployment_requests(
        self,
        *,
        environment: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        version_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._devops_read_repository.list_deployment_requests(
            environment=environment,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            status=status,
            version_id=version_id,
        )

    def page_deployment_requests(
        self,
        *,
        environment: str | None,
        page: int,
        page_size: int,
        product_id: str | None,
        product_scope_ids: list[str] | None,
        sort_by: str,
        sort_order: str,
        status: str | None,
        title: str | None,
        version_id: str | None,
    ) -> dict[str, Any]:
        return self._devops_read_repository.page_deployment_requests(
            environment=environment,
            page=page,
            page_size=page_size,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
            title=title,
            version_id=version_id,
        )

    def list_deployment_runs(
        self,
        *,
        deployment_request_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._devops_read_repository.list_deployment_runs(
            deployment_request_id=deployment_request_id,
        )

    def claim_due_deployment_runs(
        self,
        *,
        lease_seconds: int,
        limit: int,
        worker_id: str,
    ) -> list[dict[str, Any]]:
        return self._devops_read_repository.claim_due_deployment_runs(
            lease_seconds=lease_seconds,
            limit=limit,
            worker_id=worker_id,
        )

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
        exclude_category: str | None = None,
        name: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        return self._devops_read_repository.list_operational_metric_items(
            category=category,
            exclude_category=exclude_category,
            name=name,
            product_scope_ids=product_scope_ids,
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
        limit: int | None = None,
        offset: int | None = None,
        summary_only: bool = False,
    ) -> list[dict[str, Any]]:
        return self._user_insight_read_repository.list_user_feedback(
            created_by=created_by,
            feature_code=feature_code,
            limit=limit,
            module_code=module_code,
            offset=offset,
            product_id=product_id,
            status=status,
            summary_only=summary_only,
        )

    def count_user_feedback(
        self,
        *,
        product_id: str | None = None,
        module_code: str | None = None,
        feature_code: str | None = None,
        status: str | None = None,
        created_by: str | None = None,
    ) -> int:
        return self._user_insight_read_repository.count_user_feedback(
            created_by=created_by,
            feature_code=feature_code,
            module_code=module_code,
            product_id=product_id,
            status=status,
        )

    def get_user_feedback(self, feedback_id: str) -> dict[str, Any] | None:
        return self._user_insight_read_repository.get_user_feedback(feedback_id)

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
        product_id: str | None = None,
        summary: str | None = None,
        status: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        return self._user_insight_read_repository.list_user_insight_items(
            category=category,
            product_id=product_id,
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

    def count_model_gateway_configs(
        self,
        *,
        default_chat_model: str | None = None,
        default_embedding_model: str | None = None,
        embedding_connection_mode: str | None = None,
        is_default: bool | None = None,
        name: str | None = None,
        provider: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._model_gateway_read_repository.count_model_gateway_configs(
            default_chat_model=default_chat_model,
            default_embedding_model=default_embedding_model,
            embedding_connection_mode=embedding_connection_mode,
            is_default=is_default,
            name=name,
            provider=provider,
            status=status,
        )

    def list_model_gateway_configs_page(
        self,
        *,
        default_chat_model: str | None = None,
        default_embedding_model: str | None = None,
        embedding_connection_mode: str | None = None,
        is_default: bool | None = None,
        limit: int,
        name: str | None = None,
        offset: int,
        provider: str | None = None,
        sort_by: str = "name",
        sort_order: str = "asc",
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._model_gateway_read_repository.list_model_gateway_configs_page(
            default_chat_model=default_chat_model,
            default_embedding_model=default_embedding_model,
            embedding_connection_mode=embedding_connection_mode,
            is_default=is_default,
            limit=limit,
            name=name,
            offset=offset,
            provider=provider,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
        )

    def get_model_gateway_config(self, config_id: str) -> dict[str, Any] | None:
        return self._model_gateway_read_repository.get_model_gateway_config(config_id)

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

    def list_rd_task_executor_policies(
        self,
        *,
        product_id: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._task_read_repository.list_rd_task_executor_policies(
            product_id=product_id,
            status=status,
            task_type=task_type,
        )

    def list_quality_gate_policies(
        self,
        *,
        phase: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_quality_gate_policies(
            phase=phase,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            status=status,
            task_type=task_type,
        )

    def get_quality_gate_policy(self, policy_id: str) -> dict[str, Any] | None:
        return self._execution_governance_read_repository.get_quality_gate_policy(policy_id)

    def list_execution_context_manifests(
        self,
        *,
        product_scope_ids: list[str] | None = None,
        subject_id: str | None = None,
        subject_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_execution_context_manifests(
            product_scope_ids=product_scope_ids,
            subject_id=subject_id,
            subject_type=subject_type,
        )

    def list_quality_gate_runs(
        self,
        *,
        phase: str | None = None,
        product_scope_ids: list[str] | None = None,
        subject_id: str | None = None,
        subject_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_quality_gate_runs(
            phase=phase,
            product_scope_ids=product_scope_ids,
            subject_id=subject_id,
            subject_type=subject_type,
        )

    def list_quality_gate_checks(self, quality_gate_run_id: str) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_quality_gate_checks(
            quality_gate_run_id
        )

    def list_execution_attestations(
        self,
        *,
        subject_id: str | None = None,
        runner_task_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_execution_attestations(
            subject_id=subject_id,
            runner_task_id=runner_task_id,
        )

    def list_trusted_delivery_records(
        self,
        *,
        product_scope_ids: list[str] | None = None,
        record_type: str,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_trusted_delivery_records(
            product_scope_ids=product_scope_ids,
            record_type=record_type,
        )

    def list_agent_loop_runs(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_agent_loop_runs(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
        )

    def list_agent_loop_iterations(self, loop_run_id: str) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_agent_loop_iterations(loop_run_id)

    def list_execution_resource_grants(
        self,
        *,
        environment: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        resource_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_execution_resource_grants(
            environment=environment,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            resource_type=resource_type,
            status=status,
        )

    def claim_execution_outbox_events(
        self,
        *,
        lease_seconds: int,
        limit: int,
        worker_id: str,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.claim_execution_outbox_events(
            lease_seconds=lease_seconds,
            limit=limit,
            worker_id=worker_id,
        )

    def list_execution_outbox_events(
        self,
        *,
        aggregate_id: str | None = None,
        aggregate_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_execution_outbox_events(
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            status=status,
        )

    def list_deployment_run_steps(
        self,
        *,
        deployment_run_id: str,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_deployment_run_steps(
            deployment_run_id=deployment_run_id,
        )

    def claim_external_event_inbox(
        self,
        *,
        lease_seconds: int,
        limit: int,
        worker_id: str,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.claim_external_event_inbox(
            lease_seconds=lease_seconds,
            limit=limit,
            worker_id=worker_id,
        )

    def list_external_event_inbox(
        self,
        *,
        delivery_id: str | None = None,
        provider: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._execution_governance_read_repository.list_external_event_inbox(
            delivery_id=delivery_id,
            provider=provider,
            status=status,
        )

    def count_rd_task_executor_policies(
        self,
        *,
        executor_type: str | None = None,
        name: str | None = None,
        product_id: str | None = None,
        product_name: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> int:
        return self._task_read_repository.count_rd_task_executor_policies(
            executor_type=executor_type,
            name=name,
            product_id=product_id,
            product_name=product_name,
            status=status,
            task_type=task_type,
        )

    def list_rd_task_executor_policy_page(
        self,
        *,
        executor_type: str | None = None,
        limit: int,
        name: str | None = None,
        offset: int,
        product_id: str | None = None,
        product_name: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._task_read_repository.list_rd_task_executor_policy_page(
            executor_type=executor_type,
            limit=limit,
            name=name,
            offset=offset,
            product_id=product_id,
            product_name=product_name,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
            task_type=task_type,
        )

    def save_rd_task_executor_policy_record(
        self,
        record: dict[str, Any],
        *,
        expected_policy_version: int | None = None,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return RdCollaborationReadRepository.save_rd_task_executor_policy_record(
            self,
            record,
            expected_policy_version=expected_policy_version,
            audit_event=audit_event,
        )

    def delete_rd_task_executor_policy_record(
        self,
        policy_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._task_read_repository.delete_rd_task_executor_policy_record(
            policy_id,
            audit_event=audit_event,
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

    def count_scheduled_jobs(
        self,
        *,
        enabled: bool | None = None,
        job_type: str | None = None,
        keyword: str | None = None,
        name: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        source_system: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._scheduled_ai_job_read_repository.count_scheduled_jobs(
            enabled=enabled,
            job_type=job_type,
            keyword=keyword,
            name=name,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            source_system=source_system,
            status=status,
        )

    def list_scheduled_jobs_page(
        self,
        *,
        enabled: bool | None = None,
        job_type: str | None = None,
        keyword: str | None = None,
        limit: int,
        name: str | None = None,
        offset: int,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        sort_by: str,
        sort_order: str,
        source_system: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._scheduled_ai_job_read_repository.list_scheduled_jobs_page(
            enabled=enabled,
            job_type=job_type,
            keyword=keyword,
            limit=limit,
            name=name,
            offset=offset,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            sort_by=sort_by,
            sort_order=sort_order,
            source_system=source_system,
            status=status,
        )

    def list_scheduled_job_runs(
        self,
        *,
        run_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._scheduled_ai_job_read_repository.list_scheduled_job_runs(
            run_ids=run_ids,
            scheduled_job_id=scheduled_job_id,
            status=status,
        )

    def list_assistant_scoped_scheduled_job_runs(
        self,
        *,
        action_draft_ids: list[str],
        action_run_ids: list[str],
        message_ids: list[str],
        referenced_run_ids: list[str],
        since: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._scheduled_ai_job_read_repository.list_assistant_scoped_scheduled_job_runs(
            action_draft_ids=action_draft_ids,
            action_run_ids=action_run_ids,
            message_ids=message_ids,
            referenced_run_ids=referenced_run_ids,
            since=since,
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

    def count_code_inspection_reports(
        self,
        *,
        committer: str | None = None,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        repository_id: str | None = None,
        risk_level: str | None = None,
        status: str | None = None,
        title: str | None = None,
    ) -> int:
        return self._code_inspection_read_repository.count_code_inspection_reports(
            committer=committer,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            repository_id=repository_id,
            risk_level=risk_level,
            status=status,
            title=title,
        )

    def list_code_inspection_reports_page(
        self,
        *,
        committer: str | None = None,
        limit: int,
        offset: int,
        product_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        repository_id: str | None = None,
        risk_level: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
        title: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._code_inspection_read_repository.list_code_inspection_reports_page(
            committer=committer,
            limit=limit,
            offset=offset,
            product_id=product_id,
            product_scope_ids=product_scope_ids,
            repository_id=repository_id,
            risk_level=risk_level,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
            title=title,
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

    def count_plugin_connections(
        self,
        *,
        environment: str | None = None,
        keyword: str | None = None,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._plugin_read_repository.count_plugin_connections(
            environment=environment,
            keyword=keyword,
            plugin_id=plugin_id,
            status=status,
        )

    def list_plugin_connections_page(
        self,
        *,
        environment: str | None = None,
        keyword: str | None = None,
        limit: int,
        offset: int,
        plugin_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_plugin_connections_page(
            environment=environment,
            keyword=keyword,
            limit=limit,
            offset=offset,
            plugin_id=plugin_id,
            sort_by=sort_by,
            sort_order=sort_order,
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

    def count_plugin_actions(
        self,
        *,
        keyword: str | None = None,
        plugin_id: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._plugin_read_repository.count_plugin_actions(
            keyword=keyword,
            plugin_id=plugin_id,
            status=status,
        )

    def list_plugin_actions_page(
        self,
        *,
        keyword: str | None = None,
        limit: int,
        offset: int,
        plugin_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_plugin_actions_page(
            keyword=keyword,
            limit=limit,
            offset=offset,
            plugin_id=plugin_id,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
        )

    def list_plugin_invocation_logs(
        self,
        *,
        action_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_plugin_invocation_logs(
            action_id=action_id,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )

    def count_plugin_invocation_logs(
        self,
        *,
        action_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._plugin_read_repository.count_plugin_invocation_logs(
            action_id=action_id,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )

    def list_plugin_invocation_logs_page(
        self,
        *,
        action_id: str | None = None,
        limit: int,
        offset: int,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_plugin_invocation_logs_page(
            action_id=action_id,
            limit=limit,
            offset=offset,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
        )

    def count_result_write_records(
        self,
        *,
        plugin_action_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
        write_target: str | None = None,
    ) -> int:
        return self._plugin_read_repository.count_result_write_records(
            plugin_action_id=plugin_action_id,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
            write_target=write_target,
        )

    def list_result_write_records_page(
        self,
        *,
        limit: int,
        offset: int,
        plugin_action_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        scheduled_job_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
        write_target: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_result_write_records_page(
            limit=limit,
            offset=offset,
            plugin_action_id=plugin_action_id,
            product_scope_ids=product_scope_ids,
            scheduled_job_id=scheduled_job_id,
            scheduled_job_run_id=scheduled_job_run_id,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
            write_target=write_target,
        )

    def list_ai_executor_runners(
        self,
        *,
        executor_type: str | None = None,
        keyword: str | None = None,
        protocol: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_ai_executor_runners(
            executor_type=executor_type,
            keyword=keyword,
            protocol=protocol,
            status=status,
        )

    def count_ai_executor_runners(
        self,
        *,
        executor_type: str | None = None,
        keyword: str | None = None,
        protocol: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._plugin_read_repository.count_ai_executor_runners(
            executor_type=executor_type,
            keyword=keyword,
            protocol=protocol,
            status=status,
        )

    def list_ai_executor_runners_page(
        self,
        *,
        executor_type: str | None = None,
        keyword: str | None = None,
        limit: int,
        offset: int,
        protocol: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_ai_executor_runners_page(
            executor_type=executor_type,
            keyword=keyword,
            limit=limit,
            offset=offset,
            protocol=protocol,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
        )

    def list_ai_executor_tasks(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        runner_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_ai_executor_tasks(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )

    def count_ai_executor_tasks(
        self,
        *,
        ai_task_id: str | None = None,
        product_scope_ids: list[str] | None = None,
        runner_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._plugin_read_repository.count_ai_executor_tasks(
            ai_task_id=ai_task_id,
            product_scope_ids=product_scope_ids,
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            status=status,
        )

    def list_ai_executor_tasks_page(
        self,
        *,
        ai_task_id: str | None = None,
        limit: int,
        offset: int,
        product_scope_ids: list[str] | None = None,
        runner_id: str | None = None,
        scheduled_job_run_id: str | None = None,
        sort_by: str,
        sort_order: str,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._plugin_read_repository.list_ai_executor_tasks_page(
            ai_task_id=ai_task_id,
            limit=limit,
            offset=offset,
            product_scope_ids=product_scope_ids,
            runner_id=runner_id,
            scheduled_job_run_id=scheduled_job_run_id,
            sort_by=sort_by,
            sort_order=sort_order,
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

    def count_model_gateway_logs(
        self,
        *,
        ai_task_id: str | None = None,
        purpose: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._model_gateway_read_repository.count_model_gateway_logs(
            ai_task_id=ai_task_id,
            purpose=purpose,
            status=status,
        )

    def list_model_gateway_logs_page(
        self,
        *,
        ai_task_id: str | None = None,
        limit: int,
        offset: int,
        purpose: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._model_gateway_read_repository.list_model_gateway_logs_page(
            ai_task_id=ai_task_id,
            limit=limit,
            offset=offset,
            purpose=purpose,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
        )

    def refresh_execution_trace_snapshots(self, traces: list[dict[str, Any]]) -> None:
        self._execution_trace_read_repository.refresh_execution_trace_snapshots(traces)

    def count_execution_trace_snapshots(
        self,
        *,
        created_from: Any = None,
        created_to: Any = None,
        keyword: str | None = None,
        source_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> int:
        return self._execution_trace_read_repository.count_execution_trace_snapshots(
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            source_id=source_id,
            source_type=source_type,
            status=status,
        )

    def list_execution_trace_snapshots(
        self,
        *,
        created_from: Any = None,
        created_to: Any = None,
        keyword: str | None = None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        source_id: str | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._execution_trace_read_repository.list_execution_trace_snapshots(
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            source_id=source_id,
            source_type=source_type,
            status=status,
        )

    def get_execution_trace_snapshot(self, trace_id: str) -> dict[str, Any] | None:
        return self._execution_trace_read_repository.get_execution_trace_snapshot(trace_id)

    def load_assistant_chat(self) -> dict[str, Any]:
        return self._assistant_chat_read_repository.load_assistant_chat()

    def list_assistant_conversations(
        self,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        user_id: str,
    ) -> list[dict[str, Any]]:
        return self._assistant_chat_read_repository.list_assistant_conversations(
            cursor=cursor,
            limit=limit,
            user_id=user_id,
        )

    def find_reusable_assistant_conversation(
        self,
        *,
        command_signature: str,
        context_scope: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        return self._assistant_chat_read_repository.find_reusable_assistant_conversation(
            command_signature=command_signature,
            context_scope=context_scope,
            user_id=user_id,
        )

    def list_assistant_chat_runs(self, *, user_id: str) -> list[dict[str, Any]]:
        return self._assistant_chat_read_repository.list_assistant_chat_runs(user_id=user_id)

    def list_execution_trace_assistant_chat_runs(self) -> list[dict[str, Any]]:
        return self._assistant_chat_read_repository.list_execution_trace_assistant_chat_runs()

    def get_assistant_chat_run(self, *, run_id: str) -> dict[str, Any] | None:
        return self._assistant_chat_read_repository.get_assistant_chat_run(run_id=run_id)

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

    def delete_assistant_conversations(
        self,
        *,
        audit_event: dict[str, Any] | None = None,
        conversation_ids: list[str],
        user_id: str,
    ) -> dict[str, Any]:
        return self._assistant_chat_read_repository.delete_assistant_conversations(
            audit_event=audit_event,
            conversation_ids=conversation_ids,
            user_id=user_id,
        )

    def list_assistant_action_drafts(self, *, user_id: str) -> list[dict[str, Any]]:
        return self._assistant_chat_read_repository.list_assistant_action_drafts(
            user_id=user_id,
        )

    def list_assistant_action_draft_workbench_page(
        self,
        *,
        action: str | None,
        created_from: str | None,
        created_to: str | None,
        keyword: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        status: str | None,
        user_id: str,
        validation_status: str | None,
    ) -> dict[str, Any]:
        return self._assistant_chat_read_repository.list_assistant_action_draft_workbench_page(
            action=action,
            created_from=created_from,
            created_to=created_to,
            keyword=keyword,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            status=status,
            user_id=user_id,
            validation_status=validation_status,
        )

    def get_assistant_action_draft(self, *, draft_id: str) -> dict[str, Any] | None:
        return self._assistant_chat_read_repository.get_assistant_action_draft(
            draft_id=draft_id,
        )

    def list_assistant_role_quick_tasks(self) -> list[dict[str, Any]]:
        return self._assistant_chat_read_repository.list_assistant_role_quick_tasks()

    def get_assistant_role_quick_task(self, *, config_id: str) -> dict[str, Any] | None:
        return self._assistant_chat_read_repository.get_assistant_role_quick_task(
            config_id=config_id,
        )

    def save_assistant_role_quick_task_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._assistant_chat_read_repository.save_assistant_role_quick_task_record(
            record,
            audit_event=audit_event,
        )

    def delete_assistant_role_quick_task_record(
        self,
        config_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._assistant_chat_read_repository.delete_assistant_role_quick_task_record(
            config_id,
            audit_event=audit_event,
        )

    def list_assistant_action_reference_configs(self) -> list[dict[str, Any]]:
        return self._assistant_chat_read_repository.list_assistant_action_reference_configs()

    def get_assistant_action_reference_config(self, *, config_id: str) -> dict[str, Any] | None:
        return self._assistant_chat_read_repository.get_assistant_action_reference_config(
            config_id=config_id,
        )

    def save_assistant_action_reference_config_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._assistant_chat_read_repository.save_assistant_action_reference_config_record(
            record,
            audit_event=audit_event,
        )

    def delete_assistant_action_reference_config_record(
        self,
        config_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._assistant_chat_read_repository.delete_assistant_action_reference_config_record(
            config_id,
            audit_event=audit_event,
        )

    def save_assistant_action_records(
        self,
        *,
        draft: dict[str, Any],
        audit_events: list[dict[str, Any]],
        run: dict[str, Any] | None = None,
    ) -> None:
        self._assistant_chat_read_repository.save_assistant_action_records(
            draft=draft,
            audit_events=audit_events,
            run=run,
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

    def update_requirement_assessment(
        self,
        assessment: dict[str, Any],
        *,
        expected_version: int,
        audit_event: dict[str, Any] | None = None,
        requirement: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._requirement_read_repository.update_requirement_assessment(
            assessment,
            expected_version=expected_version,
            audit_event=audit_event,
            requirement=requirement,
        )

    def update_requirement_assessment_opinion(self, opinion: dict[str, Any]) -> dict[str, Any]:
        return self._requirement_read_repository.update_requirement_assessment_opinion(opinion)

    def submit_assessment_answers(
        self,
        *,
        assessment_id: str,
        expected_version: int,
        answers: dict[str, Any],
        actor_id: str,
    ) -> dict[str, Any]:
        return self._requirement_read_repository.submit_assessment_answers(
            assessment_id=assessment_id,
            expected_version=expected_version,
            answers=answers,
            actor_id=actor_id,
        )

    def get_requirement_assessment_command(
        self, *, assessment_id: str, operation: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        return self._requirement_read_repository.get_requirement_assessment_command(
            assessment_id=assessment_id, operation=operation, idempotency_key=idempotency_key
        )

    def save_requirement_assessment_command(self, command: dict[str, Any]) -> dict[str, Any]:
        return self._requirement_read_repository.save_requirement_assessment_command(command)

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

    def save_bug_and_ai_task_records(
        self,
        *,
        bug: dict[str, Any],
        task: dict[str, Any],
        audit_events: list[dict[str, Any]],
    ) -> None:
        self._task_read_repository.save_bug_and_ai_task_records(
            bug=bug,
            task=task,
            audit_events=audit_events,
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

    def save_quality_gate_policy_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
        expected_version: int | None = None,
    ) -> None:
        self._execution_governance_read_repository.save_quality_gate_policy_record(
            record,
            audit_events=audit_events,
            expected_version=expected_version,
        )

    def save_execution_context_manifest_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._execution_governance_read_repository.save_execution_context_manifest_record(
            record,
            audit_event=audit_event,
        )

    def save_execution_attestation_record(self, record: dict[str, Any]) -> None:
        self._execution_governance_read_repository.save_execution_attestation_record(record)

    def save_trusted_delivery_record(
        self,
        *,
        record: dict[str, Any],
        record_type: str,
    ) -> None:
        self._execution_governance_read_repository.save_trusted_delivery_record(
            record=record,
            record_type=record_type,
        )

    def save_execution_resource_grant_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> None:
        self._execution_governance_read_repository.save_execution_resource_grant_record(
            record,
            audit_event=audit_event,
            expected_version=expected_version,
        )

    def save_external_event_inbox_record(
        self,
        record: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._execution_governance_read_repository.save_external_event_inbox_record(
            record,
            audit_event=audit_event,
        )

    def save_quality_gate_bundle_record(
        self,
        *,
        audit_events: list[dict[str, Any]] | None,
        checks: list[dict[str, Any]],
        run: dict[str, Any],
    ) -> None:
        self._execution_governance_read_repository.save_quality_gate_bundle_record(
            audit_events=audit_events,
            checks=checks,
            run=run,
        )

    def save_agent_loop_bundle_record(
        self,
        *,
        audit_events: list[dict[str, Any]] | None,
        iterations: list[dict[str, Any]],
        run: dict[str, Any],
    ) -> None:
        self._execution_governance_read_repository.save_agent_loop_bundle_record(
            audit_events=audit_events,
            iterations=iterations,
            run=run,
        )

    def save_deployment_dispatch_result_transaction(
        self,
        *,
        audit_events: list[dict[str, Any]],
        outbox_event: dict[str, Any],
        run: dict[str, Any],
    ) -> None:
        self._execution_governance_read_repository.save_deployment_dispatch_result_transaction(
            audit_events=audit_events,
            outbox_event=outbox_event,
            run=run,
        )

    def save_execution_outbox_event_record(
        self,
        event: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._execution_governance_read_repository.save_execution_outbox_event_record(
            event,
            audit_event=audit_event,
        )

    def save_deployment_run_steps_records(
        self,
        steps: list[dict[str, Any]],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None:
        self._execution_governance_read_repository.save_deployment_run_steps_records(
            steps,
            audit_events=audit_events,
        )

    def create_deployment_dispatch_transaction(
        self,
        *,
        audit_events: list[dict[str, Any]],
        deployment: dict[str, Any],
        outbox_event: dict[str, Any],
        requirements: list[dict[str, Any]],
        run: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> None:
        self._execution_governance_read_repository.create_deployment_dispatch_transaction(
            audit_events=audit_events,
            deployment=deployment,
            outbox_event=outbox_event,
            requirements=requirements,
            run=run,
            steps=steps,
        )

    def save_deployment_dispatch_failure_transaction(
        self,
        *,
        audit_events: list[dict[str, Any]],
        deployment: dict[str, Any],
        outbox_event: dict[str, Any],
        requirements: list[dict[str, Any]],
        run: dict[str, Any],
        steps: list[dict[str, Any]],
    ) -> None:
        self._execution_governance_read_repository.save_deployment_dispatch_failure_transaction(
            audit_events=audit_events,
            deployment=deployment,
            outbox_event=outbox_event,
            requirements=requirements,
            run=run,
            steps=steps,
        )

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

    def save_deployment_request_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None:
        self._devops_read_repository.save_deployment_request_record(
            record,
            audit_events=audit_events,
        )

    def save_deployment_scheme_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
        expected_version: int | None = None,
    ) -> None:
        self._devops_read_repository.save_deployment_scheme_record(
            record,
            audit_events=audit_events,
            expected_version=expected_version,
        )

    def delete_deployment_scheme_record(
        self,
        scheme_id: str,
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None:
        self._devops_read_repository.delete_deployment_scheme_record(
            scheme_id,
            audit_events=audit_events,
        )

    def save_deployment_run_record(
        self,
        record: dict[str, Any],
        *,
        audit_events: list[dict[str, Any]] | None = None,
    ) -> None:
        self._devops_read_repository.save_deployment_run_record(
            record,
            audit_events=audit_events,
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

    def save_user_feedback_requirement_conversion(
        self,
        *,
        audit_events: list[dict[str, Any]],
        feedback: dict[str, Any],
        requirement: dict[str, Any],
    ) -> None:
        self._user_insight_read_repository.save_user_feedback_requirement_conversion(
            audit_events=audit_events,
            feedback=feedback,
            requirement=requirement,
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

    def upsert_model_gateway_config_record(
        self,
        config: dict[str, Any],
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._model_gateway_read_repository.upsert_model_gateway_config_record(
            config,
            audit_event=audit_event,
        )

    def delete_model_gateway_config_record(
        self,
        config_id: str,
        *,
        audit_event: dict[str, Any] | None = None,
    ) -> None:
        self._model_gateway_read_repository.delete_model_gateway_config_record(
            config_id,
            audit_event=audit_event,
        )

    def save_assistant_chat(self, payload: dict[str, Any]) -> None:
        self._assistant_chat_read_repository.save_assistant_chat(payload)

    def save_assistant_chat_records(
        self,
        *,
        chat_run: dict[str, Any] | None = None,
        conversation: dict[str, Any] | None,
        messages: list[dict[str, Any]],
        audit_events: list[dict[str, Any]],
        model_log: dict[str, Any] | None = None,
    ) -> None:
        self._assistant_chat_read_repository.save_assistant_chat_records(
            chat_run=chat_run,
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
